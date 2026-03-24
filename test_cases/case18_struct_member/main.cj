// 测试用例18: 结构体成员竞争
// 测试结构体成员变量的数据竞争

struct Data {
    var value: Int64
    var name: String
}

main() {
    let data = Data(value: 0, name: "test")
    
    // 线程1: 写入value
    spawn {
        data.value = 100  // 写操作
    }
    
    // 线程2: 读取value
    spawn {
        let v = data.value  // 读操作
        println(v)
    }
    
    println(data.value)
}