// 测试用例17: 循环中的数据竞争
// 测试循环内spawn创建的多个线程之间的竞争

main() {
    var counter: Int64 = 0
    
    // 循环创建多个spawn
    for (i in 0..10) {
        spawn {
            counter = counter + 1  // 写操作，多个线程竞争
        }
    }
    
    println(counter)
}