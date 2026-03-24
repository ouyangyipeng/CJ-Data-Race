// 测试用例13: 数组元素访问竞争
// 多线程访问同一数组元素

main() {
    var data: Array<Int64> = [1, 2, 3, 4, 5]
    
    // 线程1: 写数组元素
    spawn {
        data[0] = 100  // 写操作
    }
    
    // 线程2: 读数组元素
    spawn {
        let value = data[0]  // 读操作，存在RW竞争
        println(value)
    }
    
    println(data[0])
}