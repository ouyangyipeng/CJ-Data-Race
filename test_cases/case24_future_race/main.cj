// 测试用例24: Future竞争
// 测试通过Future返回值导致的竞争

main() {
    var result: Int64 = 0
    
    // 线程1: 写入result
    spawn {
        result = 100  // 写操作
    }
    
    // 线程2: 读取result
    spawn {
        println(result)  // 读操作
    }
    
    // 线程3: 写入result
    spawn {
        result = 200  // 写操作
    }
    
    println(result)
}